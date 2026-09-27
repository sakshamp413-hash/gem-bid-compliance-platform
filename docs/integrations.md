# Government Registry Integration & Adapter Architecture

PRAMAAN interfaces with external statutory portals using an extensible adapter design pattern, ensuring seamless transition from synthetic demonstration environments to authorized live government gateways.

---

## 1. The Core Adapter Seam (`GovPortalAdapter`)

All registry access is decoupled via the `GovPortalAdapter` abstract base class (`backend/app/integration/adapter.py`).

```python
class GovPortalAdapter(ABC):
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
    def check_blacklist(self, name: str, pan: str, cin: str) -> PortalResponse: ...
    
    @abstractmethod
    def digilocker_verify(self, issued_uri: str) -> PortalResponse: ...
```

Every method returns a standardized `PortalResponse` object:
```json
{
  "found": true,
  "data": {
    "legal_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
    "status": "Active",
    "filing_status": "Current"
  },
  "source": "APISetu-GSTN",
  "retrieved_at": "2026-09-27T13:45:00Z",
  "latency_ms": 142,
  "error": null
}
```

---

## 2. Supported Adapter Implementations

### 2.1 `MockGovPortal` (Seeded Offline Demo Mode)
* **Status:** Fully functional & self-contained (`data/mock_portal.json`).
* **Purpose:** Provides instantaneous, offline verification data for hackathon evaluation and air-gapped testing.
* **Labeling:** Transparently displays `● DEMO MODE — SYNTHETIC REGISTRY` across all UI headers.

### 2.2 `ApiSetuAdapter` (Production API Gateway)
* **Status:** Production-shaped adapter with endpoint contracts aligned to API Setu (MeitY).
* **Onboarding Path:**
  1. Department registers on [API Setu Portal](https://apisetu.gov.in).
  2. Generates OAuth2 Client ID and Client Secret for ITD (PAN), GSTN, and Udyam APIs.
  3. Configures environment variables:
     ```env
     PORTAL_ADAPTER=apisetu
     APISETU_CLIENT_ID=gov_client_id_here
     APISETU_CLIENT_SECRET=gov_secret_here
     ```

### 2.3 `DigiLockerAdapter` (PKI Certificate Verification)
* **Status:** Validates issued certificate URIs and root CA chains against Controller of Certifying Authorities (CCA) certificates.
