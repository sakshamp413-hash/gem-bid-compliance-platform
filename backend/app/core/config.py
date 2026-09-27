"""
Application configuration.

All values overridable via environment variables / .env file.
Secrets are never logged and never shipped in the repo.
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    # --- App ---
    app_name: str = "PRAMAAN — AI-Powered GeM Bid Compliance & Procurement Intelligence Platform"
    environment: str = "development"  # development | production
    debug: bool = True

    # --- Database ---
    # SQLite fallback (zero-config local runs); PostgreSQL via compose.
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'storage' / 'app.db'}"

    # --- Auth ---
    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # --- Field-level encryption (Fernet, key must be 32 url-safe base64 bytes) ---
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # --- Integration layer ---
    portal_adapter: str = "mock"  # mock | apisetu | gsp | digilocker
    mock_portal_data: str = str(PROJECT_ROOT / "data" / "mock_portal.json")
    portal_timeout_seconds: int = 10

    # --- AI / LLM ---
    llm_provider: str = "auto"  # auto | openai | anthropic | ollama | offline
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""  # OpenAI-compatible endpoint override
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- PKI / DigiLocker-style trust ---
    certs_dir: str = str(BACKEND_ROOT / "storage" / "certs")
    # Expected signer issuer CN for DigiLocker-style PDFs (demo CA by default).
    expected_issuer_cn: str = "Demo DigiLocker Issuing CA"
    # Real onboarding: set to the CN of the real DigiLocker/GSTN signing chain
    # and point trust_roots at the real certificates (see docs/production.md).

    # --- Storage ---
    document_storage: str = str(BACKEND_ROOT / "storage" / "documents")

    # --- Rules ---
    rules_file: str = str(PROJECT_ROOT / "backend" / "app" / "rules" / "rules.yaml")

    # --- Rate limiting (auth endpoints) ---
    auth_rate_limit_per_minute: int = 20
    # Redis URL for multi-instance rate limiting. Empty = in-process fallback.
    # Production: set REDIS_URL=redis://localhost:6379/0 (see docs/production.md).
    redis_url: str = ""

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fernet_key(self) -> bytes:
        """Return the Fernet key; generate a stable one if unset (dev only)."""
        if self.encryption_key:
            return self.encryption_key.encode()
        # Deterministic dev fallback so SQLite dev DBs stay readable across restarts.
        derived = base64.urlsafe_b64encode(
            hashlib.sha256(self.jwt_secret.encode()).digest()
        )
        return derived

    @property
    def llm_resolved_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        if self.llm_api_key:
            return "openai"
        return "offline"

    @property
    def storage_dir(self) -> Path:
        p = Path(self.document_storage)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def certs_path(self) -> Path:
        p = Path(self.certs_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


import hashlib  # noqa: E402  (used in fernet_key property)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()