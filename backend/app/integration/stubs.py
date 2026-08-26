"""
APISetu / GSP / DigiLocker adapter stubs.

These are REAL-READY integration points. They are deliberately stubs:
wire in live credentials and swap `PORTAL_ADAPTER` to activate.

Each stub documents the exact onboarding path, endpoints and parameters so a
production team can complete the wiring without redesigning the platform.
"""
from __future__ import annotations

from app.core.config import settings
from app.integration.adapter import GovPortalAdapter, PortalResponse, register_adapter


@register_adapter
class ApiSetuAdapter(GovPortalAdapter):
    """
    APISetu (api.setu.co) — the GoI's unified API gateway (UIDAI/MoF).

    ONBOARDING PATH (real):
      1. Register as a partner at https://apisetu.gov.in → get `client_id`
         + `client_secret` per subscribed API.
      2. Subscribe to: PAN verification (ITD), GSTIN search (GSTN-APISetu),
         Udyam/MSME search, DigiLocker document fetch (partner mode).
      3. Auth: OAuth2 client-credentials → `access_token` (valid ~60 min).
      4. Calls are POST/GET with `Authorization: Bearer <token>`.
      Wire credentials in env: APISETU_CLIENT_ID / APISETU_CLIENT_SECRET.

    Endpoints (illustrative, verify against current APISetu docs):
      POST https://api.setu.co/v1/pan/verify         {"pan": ...}
      POST https://api.setu.co/v1/gstin/verify       {"gstin": ...}
      POST https://api.setu.co/v1/udyam/verify       {"udyamNo": ...}
    """

    name = "apisetu"

    def _unwired(self, method: str) -> PortalResponse:
        return PortalResponse(
            found=False,
            data={},
            source=self.name,
            error=f"{method}: APISetu adapter not wired — set APISETU_CLIENT_ID/SECRET and PORTAL_ADAPTER=apisetu",
        )

    def verify_udyam(self, udyam_no: str) -> PortalResponse:
        return self._unwired("verify_udyam")

    def verify_gstin(self, gstin: str) -> PortalResponse:
        return self._unwired("verify_gstin")

    def gst_return_status(self, gstin: str) -> PortalResponse:
        return self._unwired("gst_return_status")

    def verify_pan(self, pan: str) -> PortalResponse:
        return self._unwired("verify_pan")

    def mca_company(self, cin: str) -> PortalResponse:
        return self._unwired("mca_company")

    def epfo_status(self, epfo_no: str) -> PortalResponse:
        return self._unwired("epfo_status")

    def esic_status(self, esic_no: str) -> PortalResponse:
        return self._unwired("esic_status")

    def startup_status(self, dpiit_no: str) -> PortalResponse:
        return self._unwired("startup_status")

    def nsic_status(self, nsic_no: str) -> PortalResponse:
        return self._unwired("nsic_status")

    def check_blacklist(self, name: str, pan: str | None = None, cin: str | None = None) -> PortalResponse:
        return self._unwired("check_blacklist")

    def digilocker_verify(self, issued_uri: str) -> PortalResponse:
        return self._unwired("digilocker_verify")


@register_adapter
class GSPAdapter(GovPortalAdapter):
    """
    GSP — GST Suvidha Provider (GSTN API access).

    ONBOARDING PATH (real):
      1. Become a GSP: licensed by GSTN → sign GSP agreement, get
         `gstn_username` / `gstn_password` (or mSIG based auth) for the
         GSP's own GSTIN.
      2. Integration: GSTN API v3 uses OAuth2 (`/auth/token`) + signature
         header (SHA256 HMAC of payload with the GSP's private key).
      3. Key calls: GSTIN search (`/taxpayer/gstin/{gstin}`), returns
         (GSTR-3B/1 status via `/returns/...`).
      Wire credentials in env: GSP_GSTIN / GSP_USERNAME / GSP_PASSWORD / GSP_PRIVATE_KEY.
    """

    name = "gsp"

    def _unwired(self, method: str) -> PortalResponse:
        return PortalResponse(
            found=False,
            data={},
            source=self.name,
            error=f"{method}: GSP adapter not wired — set GSP_* env and PORTAL_ADAPTER=gsp",
        )

    def verify_udyam(self, udyam_no: str) -> PortalResponse:
        return self._unwired("verify_udyam")

    def verify_gstin(self, gstin: str) -> PortalResponse:
        return self._unwired("verify_gstin")

    def gst_return_status(self, gstin: str) -> PortalResponse:
        return self._unwired("gst_return_status")

    def verify_pan(self, pan: str) -> PortalResponse:
        return self._unwired("verify_pan")

    def mca_company(self, cin: str) -> PortalResponse:
        return self._unwired("mca_company")

    def epfo_status(self, epfo_no: str) -> PortalResponse:
        return self._unwired("epfo_status")

    def esic_status(self, esic_no: str) -> PortalResponse:
        return self._unwired("esic_status")

    def startup_status(self, dpiit_no: str) -> PortalResponse:
        return self._unwired("startup_status")

    def nsic_status(self, nsic_no: str) -> PortalResponse:
        return self._unwired("nsic_status")

    def check_blacklist(self, name: str, pan: str | None = None, cin: str | None = None) -> PortalResponse:
        return self._unwired("check_blacklist")

    def digilocker_verify(self, issued_uri: str) -> PortalResponse:
        return self._unwired("digilocker_verify")


@register_adapter
class DigiLockerAdapter(GovPortalAdapter):
    """
    DigiLocker partner adapter — verifies/fetches issued documents.

    ONBOARDING PATH (real):
      1. Partner onboarding via DigiLocker (https://www.digilocker.gov.in):
         organization PAN, DSC for signing, partner key pair.
      2. OAuth2 auth-code flow with `client_id`/`client_secret`.
      3. Fetch issued doc: GET /api/v2/issueddocuments/{uri}
         Verify issuer signature (DigiLocker publishes its cert chain —
         swap into backend/storage/certs/trust_roots and set
         EXPECTED_ISSUER_CN to the DigiLocker signing CA CN).
      Wire credentials in env: DIGILOCKER_CLIENT_ID / DIGILOCKER_CLIENT_SECRET.
    """

    name = "digilocker"

    def _unwired(self, method: str) -> PortalResponse:
        return PortalResponse(
            found=False,
            data={},
            source=self.name,
            error=f"{method}: DigiLocker adapter not wired — set DIGILOCKER_* env and PORTAL_ADAPTER=digilocker",
        )

    def verify_udyam(self, udyam_no: str) -> PortalResponse:
        return self._unwired("verify_udyam")

    def verify_gstin(self, gstin: str) -> PortalResponse:
        return self._unwired("verify_gstin")

    def gst_return_status(self, gstin: str) -> PortalResponse:
        return self._unwired("gst_return_status")

    def verify_pan(self, pan: str) -> PortalResponse:
        return self._unwired("verify_pan")

    def mca_company(self, cin: str) -> PortalResponse:
        return self._unwired("mca_company")

    def epfo_status(self, epfo_no: str) -> PortalResponse:
        return self._unwired("epfo_status")

    def esic_status(self, esic_no: str) -> PortalResponse:
        return self._unwired("esic_status")

    def startup_status(self, dpiit_no: str) -> PortalResponse:
        return self._unwired("startup_status")

    def nsic_status(self, nsic_no: str) -> PortalResponse:
        return self._unwired("nsic_status")

    def check_blacklist(self, name: str, pan: str | None = None, cin: str | None = None) -> PortalResponse:
        return self._unwired("check_blacklist")

    def digilocker_verify(self, issued_uri: str) -> PortalResponse:
        return self._unwired("digilocker_verify")