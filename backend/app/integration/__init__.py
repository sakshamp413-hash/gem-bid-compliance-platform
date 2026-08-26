"""Integration layer. Importing this package registers all adapters."""
from app.integration import mock, stubs  # noqa: F401  (side-effect: registration)
from app.integration.adapter import GovPortalAdapter, PortalResponse, get_adapter  # noqa: F401

__all__ = ["GovPortalAdapter", "PortalResponse", "get_adapter"]