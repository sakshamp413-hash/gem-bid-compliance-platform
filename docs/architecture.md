# System Architecture & Technical Specifications

PRAMAAN is structured as a multi-tier decision-support platform designed to operate seamlessly alongside the Government e-Marketplace (GeM) and standard public e-procurement portals.

---

## 1. The Six-Layer Procurement Intelligence Model

```mermaid
flowchart TD
    subgraph L1["Layer 1: Tender Intelligence Layer"]
        T[GeM Tender Document / ATC PDF] --> TS[Clause Segmentation Engine]
        TS --> TR[Structured Requirements & Eligibility Conditions]
    end

    subgraph L2["Layer 2: Vendor Digital Compliance Twin"]
        D[Statutory & Technical Evidence PDFs] --> OCR[Layout-Aware OCR: PaddleOCR / pdfplumber]
        OCR --> NER[Structured Entity Resolution: GST, PAN, Udyam, CIN, Banking]
    end

    subgraph L3["Layer 3: Compliance Fusion Engine"]
        TR & NER --> RE[Deterministic YAML Rule Engine]
        RE --> SC[Multi-Factor Weighted Scoring & Risk Triage]
    end

    subgraph L4["Layer 4: Integrity & Fraud Intelligence"]
        D --> PKI[pyHanko Cryptographic Signature Verification]
        D --> TAM[pikepdf Incremental PDF Tamper & Revision Forensics]
        NER --> COL[Bipartite Collusion & Cartel Clustering Engine]
    end

    subgraph L5["Layer 5: Sovereign Human Decision & Reporting"]
        SC & PKI & TAM & COL --> DASH[Split-Screen Officer Evaluation Console]
        DASH --> OVR[Sovereign Officer Adjudication & Justified Override]
        OVR --> PDF[ReportLab Cryptographically Sealed Dossier Export]
    end

    subgraph L6["Layer 6: Evidence & Tamper-Evident Audit Fabric"]
        OVR --> AUD[Append-Only SHA-256 Hash-Chained Audit Ledger]
        AUD --> VER[/audit/verify Cryptographic Recomputation Engine]
    end
```

---

## 2. Component Directory Responsibilities

### 2.1 Backend (`backend/app`)
* **`core/`**: Configuration management via Pydantic Settings, JWT generation, bcrypt password hashing, Fernet symmetric field encryption, sliding-window rate limiting, and PII-redacting logging formatters.
* **`db/`**: SQLAlchemy 2.0 database engine, encrypted column types, database migrations via Alembic, and hash-chained audit persistence.
* **`models/`**: Declarative relational models mapping Users, Tenders, Tender Requirements, Bidders, Bid Submissions, Documents, Verification Checks, Decisions, and Audit Logs.
* **`schemas/`**: Pydantic v2 schemas enforcing strict request validation, response serialization, and anti-injection sanitization.
* **`api/`**: REST API route controllers organized by functional domain (`auth`, `tenders`, `submissions`, `documents`, `decisions`, `audit`, `anomalies`).
* **`services/`**:
  * `services/checks/`: 12+ modular compliance check executors covering GSTIN, PAN, Udyam, MCA21, EPFO, ESIC, Startup recognition, NSIC, OEM authorization, and Debarment lists.
  * `services/pipeline.py`: Orchestrator executing the complete verification pipeline from raw PDF ingestion to risk classification.
  * `services/collusion.py`: Graph-based clustering engine identifying shared bank accounts and common signatories across competing bids.
  * `services/report_service.py`: Generates official PDF compliance reports anchored to the cryptographic audit head hash.
* **`ai/`**: Layout-aware text extraction, bounding-box coordinate tracking, semantic entity matching via RapidFuzz, and sovereign AI provider abstractions (`offline`, `ollama`, `openai`).
* **`security/`**:
  * `security/signature_verify.py`: pyHanko CMS/PKCS#7 cryptographic digital signature validator.
  * `security/tamper_detect.py`: pikepdf byte-level incremental revision analyzer and post-signing tampering detector.
* **`rules/`**: Declarative compliance rules maintained as versioned YAML configurations (`rules.yaml`).
* **`integration/`**: `GovPortalAdapter` interface with interchangeable backends (`MockGovPortal`, `ApiSetuAdapter`, `DigiLockerAdapter`).

---

## 3. Frontend Architecture (`frontend/src`)
* **`api/`**: Strongly typed REST API client with automatic token refreshing and error boundary handling.
* **`auth/`**: Context provider managing session state, role validation (`officer`, `admin`, `auditor`), and route guards.
* **`components/`**: Reusable government-grade UI components:
  * `ScoreGauge`: Animated compliance score visualizer with risk band color tokens.
  * `CheckAccordion`: Interactive statutory check list with evidence deep-linking.
  * `DocViewer`: High-resolution split-screen PDF document inspector with yellow highlighted bounding-box coordinate overlays.
  * `AuditTimeline`: Chronological visual ledger of audit events with integrity status indicators.
* **`pages/`**:
  * `TendersPage.tsx`: Active procurement tenders list with extraction and evaluation progress.
  * `SubmissionsPage.tsx`: Tender bid triage table with automated risk badges and score rankings.
  * `BidderDetailPage.tsx`: The primary officer evaluation workstation featuring the split-screen evidence viewer and adjudication modal.
  * `AuditorPage.tsx`: Real-time cryptographic ledger inspection and single-click SHA-256 chain verification.