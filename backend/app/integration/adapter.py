"""
Government portal integration layer.

`GovPortalAdapter` is the seam between the platform and live statutory
registries. Every method returns a typed `PortalResponse`. The default
adapter is `MockGovPortal` (seeded synthetic data). Swappable via config
`PORTAL_ADAPTER` — real adapters (APISetu / GSP / DigiLocker partner) are
provided as stubs with full onboarding docs in their docstrings.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class PortalResponse:
    found: bool
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    retrieved_at: str = ""
    latency_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "data": self.data,
            "source": self.source,
            "retrieved_at": self.retrieved_at,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


class GovPortalAdapter(ABC):
    """Abstract interface for statutory-registry lookups."""

    name: str = "base"

    @abstractmethod
    def verify_udyam(self, udyam_no: str) -> PortalResponse: ...

    @abstractmethod
    def verify_gstin(self, gstin: str) -> PortalResponse: ...

    @abstractmethod
    def gst_return_status(self, gstin: str) -> PortalResponse: ...

    @abstractmethod
    def verify_pan(self, pan: str) -> PortalResponse: ...

    @abstractmethod
    def mca_company(self, cin: str) -> PortalResponse: ...

    @abstractmethod
    def epfo_status(self, epfo_no: str) -> PortalResponse: ...

    @abstractmethod
    def esic_status(self, esic_no: str) -> PortalResponse: ...

    @abstractmethod
    def startup_status(self, dpiit_no: str) -> PortalResponse: ...

    @abstractmethod
    def nsic_status(self, nsic_no: str) -> PortalResponse: ...

    @abstractmethod
    def check_blacklist(self, name: str, pan: str | None = None, cin: str | None = None) -> PortalResponse: ...

    @abstractmethod
    def digilocker_verify(self, issued_uri: str) -> PortalResponse: ...


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_ADAPTERS: dict[str, type[GovPortalAdapter]] = {}


def register_adapter(cls: type[GovPortalAdapter]) -> type[GovPortalAdapter]:
    _ADAPTERS[cls.name] = cls
    return cls


def get_adapter() -> GovPortalAdapter:
    """Instantiate the adapter configured via PORTAL_ADAPTER (default: mock)."""
    name = settings.portal_adapter
    if name not in _ADAPTERS:
        raise RuntimeError(
            f"Unknown portal adapter '{name}'. Available: {sorted(_ADAPTERS)}"
        )
    return _ADAPTERS[name]()