# PRAMAAN REST API Specification

This document provides the authoritative technical reference for the PRAMAAN API suite, designed according to OpenAPI 3.1 specifications.

## 1. Authentication & Base URL
* **Base URL:** `/api/v1`
* **Security Scheme:** HTTP Bearer JSON Web Tokens (JWT) signed via HMAC-SHA256 (`HS256`).
* **Header Format:** `Authorization: Bearer <access_token>`

All protected endpoints enforce Role-Based Access Control (RBAC) with three distinct institutional roles:
* `officer` — Procurement / Evaluating Officers with full review, flagging, and adjudication authority.
* `admin` — System administrators managing rule configurations, tenant parameters, and user permissions.
* `auditor` — Independent oversight personnel (CAG, CVC, internal vigilance) with read-only cryptographic audit verification privileges.

---

## 2. API Endpoints Reference

### 2.1 Authentication & User Session (`/auth`)

#### `POST /auth/token`
Authenticates user credentials and issues an access token and refresh token.
* **Rate Limit:** 20 requests per minute per IP address.
* **Content-Type:** `application/x-www-form-urlencoded`
* **Request Parameters:**
  * `username` (string, required): Registered official email (e.g., `officer@gem.gov.in`).
  * `password` (string, required): User password.
* **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "officer",
  "name": "S. K. Sharma",
  "department": "Public Works & Procurement"
}
```
* **Error Responses:**
  * `401 Unauthorized`: Invalid credentials or inactive account.
  * `429 Too Many Requests`: Exceeded auth rate limit.

#### `GET /auth/me`
Retrieves current authenticated identity and permission scope.
* **Headers:** `Authorization: Bearer <token>`
* **Response (200 OK):**
```json
{
  "id": "usr_9981a2f1",
  "email": "officer@gem.gov.in",
  "name": "S. K. Sharma",
  "role": "officer",
  "is_active": true
}
```

---

### 2.2 Tenders & Requirement Extraction (`/tenders`)

#### `GET /tenders`
Lists all procurement tenders under evaluation.
* **Query Parameters:**
  * `status` (string, optional): Filter by `active`, `evaluated`, `archived`.
  * `skip` (int, default: 0), `limit` (int, default: 50).
* **Response (200 OK):**
```json
[
  {
    "id": "tnd_2026_pump_001",
    "tender_number": "GeM/2026/B/1234567",
    "title": "Supply and Commissioning of Industrial Submersible Pumps",
    "category": "Mechanical Goods",
    "estimated_value": 45000000.0,
    "closing_date": "2026-10-15T15:00:00Z",
    "submission_count": 7,
    "evaluated_count": 7,
    "created_at": "2026-08-10T10:00:00Z"
  }
]
```

#### `POST /tenders/parse`
Ingests an unstructured GeM Tender Document or ATC (Additional Terms and Conditions) PDF and extracts structured compliance rules.
* **Role:** `admin`, `officer`
* **Form Data:** `file` (PDF binary)
* **Response (200 OK):**
```json
{
  "tender_id": "tnd_2026_pump_001",
  "parsed_clauses_count": 18,
  "mandatory_requirements": [
    {
      "requirement_code": "EXP_MIN_YEARS",
      "clause_reference": "ATC Clause 3.1",
      "category": "past_experience",
      "description": "Bidder must possess minimum 5 years experience in supplying industrial pumps",
      "threshold": 5,
      "unit": "years",
      "mandatory": true,
      "required_evidence": ["work_order", "experience_certificate"]
    },
    {
      "requirement_code": "MII_LOCAL_CONTENT",
      "clause_reference": "Make in India Preference Clause",
      "category": "local_content",
      "description": "Minimum 50% local content required for Class-I preference",
      "threshold": 50,
      "unit": "percent",
      "mandatory": true,
      "required_evidence": ["make_in_india_declaration", "ca_certificate"]
    }
  ]
}
```

---

### 2.3 Submissions & Compliance Verification (`/submissions`)

#### `GET /tenders/{tender_id}/submissions`
Retrieves all bidder submissions for a given tender, including compliance score and risk triage status.
* **Response (200 OK):**
```json
[
  {
    "submission_id": "sub_clean_001",
    "bidder_name": "CleanCorp Industrial Solutions Pvt. Ltd.",
    "cin": "U29100MH2015PTC267890",
    "pan": "AAACC1234D",
    "compliance_score": 95.0,
    "risk_level": "LOW",
    "system_recommendation": "QUALIFY",
    "flags_count": 0,
    "decision_status": "PENDING"
  },
  {
    "submission_id": "sub_border_002",
    "bidder_name": "Borderline Traders",
    "cin": "U51909DL2018PTC334567",
    "pan": "AABCB5678E",
    "compliance_score": 87.5,
    "risk_level": "MEDIUM",
    "system_recommendation": "NEEDS_REVIEW",
    "flags_count": 2,
    "decision_status": "PENDING"
  }
]
```

#### `GET /submissions/{submission_id}`
Retrieves complete forensic and compliance audit details for a specific bidder submission.
* **Response (200 OK):**
```json
{
  "submission_id": "sub_fraud_003",
  "bidder_name": "FraudFillers Engineering Works",
  "score": 25.0,
  "risk_level": "HIGH",
  "recommendation": "DISQUALIFY",
  "integrity_summary": {
    "pki_valid": false,
    "tamper_detected": true,
    "collusion_detected": false,
    "debarment_found": true
  },
  "checks": [
    {
      "check_code": "STAT_GST_ACTIVE",
      "status": "FAIL",
      "title": "GSTIN Validity & Return Status",
      "reason": "GST certificate signature invalid; document modified post-signing.",
      "evidence_document": "GST_Registration_Certificate.pdf",
      "bounding_box": {"page": 1, "x": 120, "y": 340, "w": 280, "h": 22},
      "confidence": 0.99
    }
  ]
}
```

---

### 2.4 Human-in-the-Loop Adjudication (`/decisions`)

#### `POST /submissions/{submission_id}/decision`
Records the sovereign human officer's qualification or disqualification decision, mandating justification and triggering an immutable audit entry.
* **Role:** `officer`
* **Request Body:**
```json
{
  "decision": "DISQUALIFIED",
  "override_recommendation": false,
  "justification": "Document tampering verified via cryptographic hash check. Failed mandatory statutory compliance.",
  "conditions": []
}
```
* **Response (200 OK):**
```json
{
  "decision_id": "dec_88192bca",
  "submission_id": "sub_fraud_003",
  "officer_id": "usr_9981a2f1",
  "status": "DISQUALIFIED",
  "timestamp": "2026-09-27T13:40:00Z",
  "audit_sequence_id": 412,
  "ledger_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

### 2.5 Cross-Bidder Collusion Intelligence (`/anomalies`)

#### `GET /tenders/{tender_id}/collusion`
Analyzes all submitted bids for a tender and returns bipartite graph clusters connecting entities with shared attributes.
* **Response (200 OK):**
```json
{
  "tender_id": "tnd_2026_pump_001",
  "clusters_detected": 1,
  "clusters": [
    {
      "cluster_id": "cl_bank_signatory_01",
      "severity": "CRITICAL",
      "relationship_type": "SHARED_FINANCIAL_AND_SIGNATORY",
      "bidders": [
        {"id": "sub_frontrunner", "name": "FrontRunner Pumps Pvt. Ltd."},
        {"id": "sub_quickspares", "name": "QuickSpares Trading Co."}
      ],
      "shared_attributes": [
        {
          "attribute_type": "bank_account",
          "value": "HDFC50200012345678",
          "bank_name": "HDFC Bank Ltd"
        },
        {
          "attribute_type": "authorized_signatory",
          "value": "K. Verma",
          "similarity": 1.0
        }
      ],
      "investigation_recommendation": "Flag for potential bid-rigging / cartel violation under Competition Act 2002."
    }
  ]
}
```

---

### 2.6 Cryptographic Audit & Ledger Verification (`/audit`)

#### `GET /audit/ledger`
Retrieves chronological audit events with pagination.
* **Role:** `auditor`, `admin`
* **Query Parameters:** `offset`, `limit`
* **Response (200 OK):**
```json
[
  {
    "sequence_id": 105,
    "timestamp": "2026-09-27T12:15:32Z",
    "actor": "officer@gem.gov.in",
    "action": "RECORD_DECISION",
    "entity_type": "bid_submission",
    "entity_id": "sub_border_002",
    "payload_hash": "a1b2c3d4e5f6...",
    "previous_hash": "9876543210ab...",
    "current_hash": "f0e1d2c3b4a5..."
  }
]
```

#### `POST /audit/verify`
Recomputes the cryptographic SHA-256 hash sequence from genesis block 0 to the current ledger head.
* **Role:** `auditor`, `admin`
* **Response (200 OK):**
```json
{
  "status": "INTACT",
  "total_records_verified": 412,
  "genesis_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "head_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "broken_sequence_id": null,
  "verified_at": "2026-09-27T13:42:15Z"
}
```

---

### 2.7 Vendor Self-Service Pre-Check (`/vendor`)

#### `POST /vendor/pre-check`
Allows prospective bidders to validate their statutory documents against a published tender prior to formal bid submission.
* **Response (200 OK):**
```json
{
  "readiness_score": 87.5,
  "summary": {
    "total_requirements": 8,
    "satisfied": 7,
    "gaps": 1,
    "expiring_soon": 1
  },
  "actionable_gaps": [
    {
      "requirement": "GST Return Filing",
      "status": "FAIL",
      "observation": "GSTR-3B for Q3 FY 2025-26 not found in registry records.",
      "remediation": "File overdue quarterly return on GST portal and re-verify."
    }
  ]
}
```
