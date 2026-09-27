# Database Architecture & Entity Specifications

PRAMAAN utilizes a relational-first data architecture modeled using SQLAlchemy 2.0 with complete support for both SQLite (zero-config local/offline demo mode) and PostgreSQL 16 (production enterprise deployment).

---

## 1. Schema & Table Definitions

### 1.1 Core Entities

#### `users`
Stores authenticated users across three institutional roles:
* `id` (VARCHAR, PK): Unique user identifier.
* `email` (VARCHAR, UK, Indexed): Government official email address.
* `hashed_password` (VARCHAR): Passlib/bcrypt password hash (cost factor 12).
* `name` (VARCHAR): Full name and designation.
* `role` (VARCHAR): Enum (`officer`, `admin`, `auditor`).
* `is_active` (BOOLEAN): Soft-activation flag.
* `created_at` (TIMESTAMP): Creation timestamp.

#### `tenders`
Stores published GeM tender records and high-level evaluation parameters:
* `id` (VARCHAR, PK): Primary key identifier.
* `tender_number` (VARCHAR, UK, Indexed): GeM tender reference (e.g., `GeM/2026/B/1234567`).
* `title` (VARCHAR): Tender description.
* `category` (VARCHAR): Procurement category (e.g., `Mechanical Goods`).
* `estimated_value` (FLOAT): Estimated procurement value in INR.
* `closing_date` (TIMESTAMP): Submission deadline.
* `created_at` (TIMESTAMP): Record creation timestamp.

#### `bidders`
Persistent profile of bidding organizations:
* `id` (VARCHAR, PK): Primary key identifier.
* `legal_name` (VARCHAR, Indexed): Formal registered entity name.
* `pan` (EncryptedString, Indexed): Permanent Account Number (stored Fernet-encrypted).
* `gstin` (EncryptedString, Indexed): Goods and Services Tax Identification Number.
* `udyam_registration` (VARCHAR, Indexed): MSME Udyam certificate reference.
* `cin` (VARCHAR, Indexed): Corporate Identification Number from MCA21.
* `enterprise_type` (VARCHAR): `MICRO`, `SMALL`, `MEDIUM`, or `LARGE`.
* `declared_local_content_class` (VARCHAR): `CLASS_1`, `CLASS_2`, or `NON_LOCAL`.

#### `bid_submissions`
Tender-specific submission records:
* `id` (VARCHAR, PK): Primary key identifier.
* `tender_id` (VARCHAR, FK -> `tenders.id`): Parent tender.
* `bidder_id` (VARCHAR, FK -> `bidders.id`): Submitting vendor.
* `submission_time` (TIMESTAMP): Formal submission timestamp.
* `compliance_score` (FLOAT): Calculated score (0.0 to 100.0).
* `risk_category` (VARCHAR): `LOW`, `MEDIUM`, `HIGH`.
* `system_recommendation` (VARCHAR): `QUALIFY`, `NEEDS_REVIEW`, `DISQUALIFY`.
* `status` (VARCHAR): `PENDING_REVIEW`, `QUALIFIED`, `DISQUALIFIED`, `WAIVED`.

#### `documents`
Uploaded statutory and technical evidence files:
* `id` (VARCHAR, PK): Primary key identifier.
* `submission_id` (VARCHAR, FK -> `bid_submissions.id`): Associated bid submission.
* `document_type` (VARCHAR): Enum (`gst`, `pan`, `udyam`, `mca`, `epfo`, `esic`, `oem`, `turnover_ca`, `local_content_declaration`).
* `file_name` (VARCHAR): Original uploaded file name.
* `file_path` (VARCHAR): Encrypted filesystem or S3 object URI.
* `sha256_hash` (VARCHAR(64), UK, Indexed): Content digest computed before storage.
* `is_pki_signed` (BOOLEAN): Digital signature presence flag.
* `signature_valid` (BOOLEAN): Certificate chain and digest validity flag.
* `is_tampered` (BOOLEAN): Incremental revision and structural tampering indicator.
* `tamper_evidence` (JSON): Forensic findings (e.g., revision counts, `/ModDate` diffs).
* `extracted_metadata` (JSON): Layout-aware extracted entities with bounding box coordinates.

#### `verification_checks`
Individual rule evaluations executed by the compliance engine:
* `id` (VARCHAR, PK): Primary key identifier.
* `submission_id` (VARCHAR, FK -> `bid_submissions.id`): Associated bid.
* `check_code` (VARCHAR, Indexed): Policy rule code (e.g., `STAT_GST_ACTIVE`, `MII_LOCAL_CONTENT`).
* `category` (VARCHAR): `statutory`, `technical`, `financial`, `integrity`.
* `status` (VARCHAR): `PASS`, `FLAG`, `FAIL`.
* `score_contribution` (FLOAT): Weight contribution to overall score.
* `title` (VARCHAR): Human-readable check title.
* `reason` (TEXT): Plain-language justification and observation.
* `evidence_document_id` (VARCHAR, FK -> `documents.id`, Nullable): Source document reference.
* `bounding_box` (JSON, Nullable): Coordinates `{page, x, y, w, h}` on source document.
* `confidence` (FLOAT): Extraction and match confidence (0.0 to 1.0).

#### `officer_decisions`
Sovereign human adjudication records:
* `id` (VARCHAR, PK): Primary key identifier.
* `submission_id` (VARCHAR, FK -> `bid_submissions.id`, UK): Unique per submission.
* `officer_id` (VARCHAR, FK -> `users.id`): Adjudicating officer.
* `final_status` (VARCHAR): `QUALIFIED`, `DISQUALIFIED`, `CONDITIONAL_WAIVER`.
* `override_recommendation` (BOOLEAN): True if human reversed system recommendation.
* `justification` (TEXT): Mandatory written justification (minimum 15 characters).
* `decided_at` (TIMESTAMP): Adjudication timestamp.

#### `audit_log`
Cryptographically chained, append-only institutional event ledger:
* `sequence_id` (BIGINT, PK, Auto-increment): Monotonically increasing sequence index.
* `timestamp` (TIMESTAMP, Indexed): UTC event timestamp.
* `actor_id` (VARCHAR): Email or identifier of acting user or system process.
* `action_type` (VARCHAR): `INGEST_DOCUMENT`, `EXECUTE_RULES`, `FLAG_ANOMALY`, `RECORD_DECISION`, `TAMPER_DETECTED`.
* `entity_type` (VARCHAR): `bid_submission`, `document`, `tender`, `decision`.
* `entity_id` (VARCHAR): Target entity identifier.
* `payload_hash` (VARCHAR(64)): SHA-256 digest of normalized JSON event payload.
* `previous_hash` (VARCHAR(64)): Hash of preceding block (`seq - 1`).
* `current_hash` (VARCHAR(64), UK, Indexed): `SHA256(seq|timestamp|actor|action|payload_hash|prev_hash)`.

---

## 2. Field-Level Encryption (`EncryptedString`)
To protect sensitive bidder information (e.g., PAN, GSTIN, Bank Accounts) while maintaining relational querying capabilities:
* Uses Python `cryptography.fernet.Fernet` symmetric authenticated encryption (AES-128 in CBC mode with HMAC-SHA256).
* The encryption key is sourced strictly from `ENCRYPTION_KEY` environment variable.
* Plaintext is encrypted automatically on database write and decrypted transparently on model access.

---

## 3. Database Indexes & Performance Optimization
* **Compound Indexes:**
  * `bid_submissions(tender_id, compliance_score)` — High-speed triage ranking.
  * `verification_checks(submission_id, status)` — Fast aggregation of flags and failures.
  * `documents(submission_id, document_type)` — Accelerated split-view document lookup.
* **Audit Chaining Index:**
  * `audit_log(sequence_id, current_hash)` — Constant-time verification lookups.
