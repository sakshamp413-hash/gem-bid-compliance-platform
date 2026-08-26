"""
Provider-agnostic LLM client.

  * `LLMClient` — interface: `complete_json(system, user, schema_hint)`.
  * `OpenAICompatClient` — any OpenAI-compatible /chat/completions endpoint
    (OpenAI, Ollama, vLLM, LM Studio...).
  * `OfflineFallback` — deterministic responder. The full platform works
    with zero internet and zero API keys. It never invents data: it only
    echoes evidence already gathered by the deterministic engine.

All clients are strictly grounded: the system prompt forbids asserting
anything not present in the provided evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GROUNDING_SYSTEM_PROMPT = (
    "You are a strict compliance analyst for Indian government procurement. "
    "You only assert what the provided evidence supports. If a value is unknown, "
    "you output \"unknown\" or \"needs document\" — you never invent registry data, "
    "never invent statutory thresholds, and never cite sources that were not provided. "
    "Return JSON matching the requested schema exactly."
)


class LLMClient(ABC):
    provider: str = "base"

    @abstractmethod
    def complete_json(self, system: str, user: str, schema_hint: str = "object") -> dict[str, Any]: ...

    def model_meta(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": getattr(self, "model", "")}

    def prompt_hash(self, system: str, user: str) -> str:
        return hashlib.sha256((system + user).encode("utf-8")).hexdigest()[:16]


class OpenAICompatClient(LLMClient):
    """Any OpenAI-compatible chat completions endpoint."""

    provider = "openai_compat"

    def __init__(self, api_key: str, base_url: str = "", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model

    def complete_json(self, system: str, user: str, schema_hint: str = "object") -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as exc:
            logger.warning("LLM call failed (%s) — caller may fall back", exc)
            raise


class OllamaClient(OpenAICompatClient):
    provider = "ollama"

    def __init__(self, base_url: str = "", model: str = "llama3.2"):
        super().__init__(api_key="ollama", base_url=base_url or settings.ollama_base_url, model=model)


class OfflineFallback(LLMClient):
    """
    Deterministic offline responder.

    `complete_json` routes to small dedicated "analyzers" keyed by the
    schema hint so the offline demo still produces grounded, evidence-linked
    output without a model.
    """

    provider = "offline_deterministic"
    model = "deterministic-v1"

    def complete_json(self, system: str, user: str, schema_hint: str = "object") -> dict[str, Any]:
        # The caller embeds a "TASK:" marker in the user prompt; offline mode
        # dispatches to deterministic analyzers in extraction/cross_verify.
        task = re.search(r"TASK:\s*(\w+)", user)
        marker = task.group(1) if task else "generic"
        from app.ai import offline_tasks

        handler = getattr(offline_tasks, f"task_{marker}", None)
        if handler is None:
            logger.warning("offline task '%s' not found — returning empty", marker)
            return {}
        return handler(user)


def get_llm_client() -> LLMClient:
    """Factory: resolves provider from settings (auto → api key or offline)."""
    provider = settings.llm_resolved_provider
    if provider == "openai":
        return OpenAICompatClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
    if provider == "anthropic":
        # Anthropic's API is OpenAI-incompatible; route through our compat
        # adapter if a base URL is configured, else fall back to offline.
        logger.warning("anthropic provider requires an OpenAI-compatible gateway; falling back to offline")
        return OfflineFallback()
    if provider == "ollama":
        return OllamaClient(base_url=settings.ollama_base_url, model=settings.ollama_model)
    return OfflineFallback()