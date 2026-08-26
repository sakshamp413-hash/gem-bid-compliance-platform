# Going to production: swapping the mock integration for live APIs

This document is the integration-credibility story: exactly how the platform connects to real
government registries without redesigning a single check module, plus the production security
checklist.

## 1. The adapter seam

All registry access goes through `GovPortalAdapter`
(`backend/app/integration/adapter.py`):

```python
class GovPortalAdapter(ABC):
    def verify_udyam(udyam_no) -> PortalResponse
    def verify_gstin(gstin) -> PortalResponse
    def gst_return_status(gstin) -> PortalResponse
    def verify_pan(pan) -> PortalResponse
    def mca_company(cin) -> PortalResponse
    def epfo_status(epfo_no) -> PortalResponse
    def esic_status(esic_no) -> PortalResponse
    def startup_status(dpiit_no) -> PortalResponse
    def nsic_status(nsic_no) -> PortalResponse
    def check_blacklist(name, pan, cin) -> PortalResponse
    def digilocker_verify(issued_uri) -> PortalResponse
```

Every method returns a typed `PortalResponse{found, data, source, retrieved_at, latency_ms, error}`.
Adapters are registered by name; switching is one env var:

```
PORTAL_ADAPTER=apisetu | gsp | digilocker
```

Check modules, scoring, the AI engine and the UI consume only `PortalResponse` — they are
integration-agnostic by construction.

## 2. APISetu (api.setu.co) — GoI API gateway

**Onboarding path**
1. Register as a partner at <https://apisetu.gov.in> → obtain `client_id` + `client_secret` per
   subscribed API.
2. Subscribe to: PAN verification (ITD), GSTIN search (GSTN-APISetu), Udyam/MSME search,
   DigiLocker document fetch.
3. OAuth2 client-credentials flow → `access_token` (~60 min validity).
4. Wire env: `APISETU_CLIENT_ID`, `APISETU_CLIENT_SECRET`, `PORTAL_ADAPTER=apisetu`.

**Endpoint map** (verify against current APISetu docs at integration time):
| Platform method | Endpoint |
|---|---|
| `verify_pan` | `POST /v1/pan/verify  {"pan": …}` |
| `verify_gstin` | `POST /v1/gstin/verify {"gstin": …}` |
| `verify_udyam` | `POST /v1/udyam/verify {"udyamNo": …}` |
| `digilocker_verify` | `GET /v1/digilocker/documents/{uri}` (partner mode) |

Implement by filling in `ApiSetuAdapter` (`backend/app/integration/stubs.py`) — the abstract
methods are already stubbed with the exact payload/endpoint notes.

## 3. GSP (GST Suvidha Provider) — GSTN API

**Onboarding path**
1. GSTN licenses GSPs; sign the GSP agreement, obtain `gstn_username`/`gstn_password` (or mSIG
   based auth) for the GSP's own GSTIN.
2. GSTN API v3: OAuth2 at `/auth/token`, plus an HMAC-SHA256 signature header over the payload
   using the GSP's private key.
3. Key calls: `GET /taxpayer/gstin/{gstin}` (registration status + legal name),
   return-filing via GSTR-3B/1 summaries.
4. Wire env: `GSP_GSTIN`, `GSP_USERNAME`, `GSP_PASSWORD`, `GSP_PRIVATE_KEY`, `PORTAL_ADAPTER=gsp`.

`gst_return_status` maps to the latest filed-return query — the platform flags "returns not
filed / cancelled" with the exact period in evidence.

## 4. DigiLocker (partner) — issued-document verification

**Onboarding path**
1. Partner onboarding at <https://www.digilocker.gov.in> (org PAN, DSC, partner key pair).
2. OAuth2 auth-code flow with `client_id`/`client_secret`.
3. Fetch issued documents via `GET /api/v2/issueddocuments/{uri}`.

**PKI trust-root swap (the important part).** DigiLocker-issued PDFs carry an embedded PKI
signature by the DigiLocker signing CA. Today the platform validates against the demo CA:

```
backend/storage/certs/demo_ca.pem        ← replace with DigiLocker root/intermediate CAs
EXPECTED_ISSUER_CN=Demo DigiLocker Issuing CA   ← set to the real signing CA CN
```

No code changes are needed — `signature_verify.py` validates digest, chain, trust and
issuer-CN match; `tamper_detect.py` is chain-agnostic.

## 5. Blacklisting

Replace `check_blacklist` with a lookup against the GeM banned-vendor list and/or the CPP
(debarment) registry via APISetu or an authorized data feed. The check module already performs
exact PAN/CIN + fuzzy name matching against the returned list.

## 6. Production security checklist

- [ ] `JWT_SECRET`: 32+ random bytes from a secrets manager.
- [ ] `ENCRYPTION_KEY`: Fernet key from KMS; never in the repo.
- [ ] Swap demo CA → real DigiLocker/GSTN/MCA trust roots; set `EXPECTED_ISSUER_CN`.
- [ ] PostgreSQL + TLS; restrict DB network; least-privilege DB role.
- [ ] Rate limiting → Redis-backed limiter for multi-instance deployments
      (`app/core/rate_limit.py` is deliberately swappable).
- [ ] Put the API behind the org gateway (authn → mTLS → WAF); log audit events to a WORM store
      (the hash chain protects against silent edits; an immutable sink protects the chain itself).
- [ ] Review the editable rule set (`app/rules/rules.yaml`) against current DPIIT/MSME/GeM policy
      — every threshold is configurable and labeled for verification.
- [ ] OCR: install PaddleOCR for scanned-document ingestion; keep pdfplumber fallback.
- [ ] LLM: pin `LLM_MODEL`, keep `temperature=0` and the grounding system prompt; log
      `model_meta` (provider/model/prompt hash) per assessment.
- [ ] Load-test `/submissions/{id}/assess`; the pipeline is idempotent and re-runnable.