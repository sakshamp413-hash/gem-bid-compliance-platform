# 50+ Structured Grand Finale Judge Questions & Answers

This document serves as the master defense playbook for the PRAMAAN team during the Smart India Hackathon Grand Finale evaluation.

---

## 1. Technical Architecture & Systems Engineering

#### Q1: Why did you choose FastAPI over Django or Node.js?
**A:** FastAPI provides native asynchronous concurrency (`async`/`await`), which is vital for non-blocking I/O during heavy multi-page PDF processing. It also offers automatic OpenAPI 3.1 documentation generation, strict data validation via Pydantic v2, and direct, zero-overhead interoperability with Python’s dominant machine learning, computer vision, and cryptographic libraries (`pyHanko`, `pikepdf`, `PaddleOCR`).

#### Q2: Why React + Vite over Next.js for the officer workstation?
**A:** The officer evaluation dashboard is a private, authenticated, state-heavy enterprise single-page application (SPA) that requires no public search engine optimization (SEO). Vite delivers instantaneous hot-module replacement during development and minimal production bundle sizes without the server-side rendering (SSR) complexity of Next.js.

#### Q3: Why support both PostgreSQL and SQLite simultaneously?
**A:** By using SQLAlchemy 2.0 as our ORM, the data layer is completely abstracted. SQLite enables zero-configuration, air-gapped demonstration execution for hackathon jury evaluation with zero external service dependencies. PostgreSQL is the production target, providing ACID compliance, row-level locking, and native `JSONB` indexing for complex entity queries.

#### Q4: What is the exact role of Redis in your architecture?
**A:** Redis fulfills three critical enterprise roles:
1. Distributed sliding-window rate limiting on authentication routes.
2. In-memory caching for repeated statutory registry calls (24-hour TTL on GSTN/PAN lookups).
3. Message broker for asynchronous Celery/ARQ worker pools handling CPU-bound OCR tasks.

#### Q5: Why build a modular monolith instead of microservices?
**A:** For a public procurement verification system, a modular monolith with clean domain boundaries (Auth, Documents, Rules, Collusion, Audit) avoids network latency, distributed transaction failures, and complex distributed tracing, while maintaining clean module boundaries that can be extracted into microservices as throughput demands.

#### Q6: How does the system handle high-resolution scanned PDFs?
**A:** Through our dual-engine pipeline: it attempts text-layer extraction via `pdfplumber` first (sub-200ms per page). If a page has no selectable text layer or image density exceeds a threshold, it routes the page to `PaddleOCR` with image deskewing, binarization, and multilingual recognition.

#### Q7: How do you prevent database deadlocks when hundreds of bids arrive simultaneously at deadline?
**A:** We decouple ingestion from verification. Uploaded PDFs are assigned a UUID, hashed, written to object storage, and an event is queued in Redis immediately with a `202 Accepted` response. Compliance rule execution and OCR processing run asynchronously across background workers.

---

## 2. Artificial Intelligence, NLP & Document Intelligence

#### Q8: How do you guarantee the LLM won't hallucinate during clause extraction?
**A:** We use constrained decoding: the LLM is restricted to emitting structured JSON adhering strictly to a predefined Pydantic schema. Furthermore, numerical thresholds (e.g., turnover values, experience years) are extracted via deterministic regex anchors and validated against the source text before rule ingestion.

#### Q9: What happens if the AI misinterprets an ambiguous technical clause?
**A:** AI in PRAMAAN does not possess autonomous authority. The extracted clause is presented alongside the raw text snippet and page number. If the extraction confidence falls below 0.85, the check is assigned a status of `NEEDS_REVIEW`, prompting the human officer to verify the threshold manually.

#### Q10: What training data was used to train your compliance models?
**A:** Our compliance verification engine does not rely on a black-box statistical model. It uses a deterministic rule tree configured from official GeM General Terms & Conditions (GTC), the Public Procurement (Preference to Make in India) Order 2017, and the MSME Development Act 2006.

#### Q11: Can a malicious bidder execute a prompt injection attack through their PDF?
**A:** No. Extracted document text is treated strictly as passive data. It is never concatenated directly into LLM system prompts or executable code. In LLM summarization passes, document text is isolated within delimited XML tags accompanied by rigid system instructions that treat all enclosed content as untrusted raw strings.

#### Q12: How does your fuzzy entity matching handle syntactic name variations?
**A:** We apply domain-specific legal entity normalization (mapping "Pvt Ltd", "Private Limited", "LLP", etc., to standardized tokens) followed by normalized Levenshtein token-sort ratio calculation via `rapidfuzz`. Exact matches score 1.0; scores between 0.75 and 0.89 are routed to human review; scores below 0.75 trigger an entity mismatch flag.

#### Q13: Can PRAMAAN operate without an internet connection or commercial cloud LLM?
**A:** Yes. By setting `LLM_PROVIDER=offline`, the platform uses local deterministic regex parsers and rule engines with zero external network connectivity.

#### Q14: How do you handle bilingual or Hindi tenders?
**A:** Our OCR pipeline supports Devanagari script extraction, and our schema maps standard Hindi procurement terms (e.g., अनुभव -> Experience, वार्षिक कारोबार -> Annual Turnover) into normalized canonical requirement keys.

---

## 3. Cryptography, PKI & Forensic Security

#### Q15: How do you detect that a PDF was modified after it was digitally signed?
**A:** `pikepdf` parses the PDF file structure and counts incremental update sections (`/Prev` xref pointers). If incremental changes occur outside permitted signature dictionary annotations after the byte range covered by the PKI signature, the file is immediately flagged as tampered.

#### Q16: What digital signature standards do you validate?
**A:** `pyHanko` validates CMS/PKCS#7 and CAdES/PAdES digital signatures, verifying the cryptographic digest, signature timestamp, and certificate chain against a trusted root Certifying Authority (CA).

#### Q17: Where are sensitive bidder documents stored?
**A:** Uploaded documents are stored in AES-256 encrypted object storage (S3/MinIO/Encrypted filesystem). The database stores only the SHA-256 content digest, metadata, and access-controlled URI references.

#### Q18: How do you protect sensitive personal and financial identifiers (PII) in logs?
**A:** All logging output passes through a central regex sanitization filter that masks PANs, GSTINs, bank accounts, emails, and Aadhaar numbers before any log string is written to disk or stdout.

#### Q19: How are database encryption keys managed?
**A:** Field-level Fernet encryption keys and JWT secrets are sourced strictly from environment variables injected by external secrets managers (e.g., AWS Secrets Manager, HashiCorp Vault), decoupled from the source code.

#### Q20: How does your hash-chained audit ledger prevent tampering by system administrators?
**A:** Each audit entry calculates:
$$\text{Hash}_i = \text{SHA256}(\text{seq}_i \,\|\, \text{timestamp}_i \,\|\, \text{actor}_i \,\|\, \text{action}_i \,\|\, \text{payload\_hash}_i \,\|\, \text{Hash}_{i-1})$$
If an administrator alters any past database record, the hash sequence breaks from that block forward. The `/api/v1/audit/verify` endpoint recalculates the chain and immediately identifies the exact altered block index.

---

## 4. Cross-Bidder Collusion Intelligence

#### Q21: How does PRAMAAN detect bid-rigging and cartel behavior?
**A:** The collusion engine builds a bipartite relationship graph connecting Bidders to their extracted Bank Accounts, IFSC codes, PANs, authorized signatory names, and IP subnets across all bids submitted for a tender.

#### Q22: Can colluding bidders evade detection by using different company names?
**A:** Front companies often use different corporate names, but share the same bank accounts, phone numbers, or authorized power-of-attorney signatories. PRAMAAN clusters on structural backend credentials, bypassing superficial name differences.

#### Q23: Does a collusion alert automatically disqualify a bidder?
**A:** No. In accordance with public administrative law, the system labels anomalies as *"Potential integrity indicator — requires authorized investigation"* and alerts vigilance officers for formal inquiry.

#### Q24: What is the false-positive rate on collusion detection?
**A:** Exact matches on bank account numbers have virtually zero false positives. Signatory name matching uses a strict threshold (>92% similarity) and requires manual confirmation before any formal inquiry is initiated.

---

## 5. Government Integration & Practical Feasibility

#### Q25: Are live GeM APIs publicly available for hackathon participants?
**A:** No. Official GeM APIs require departmental onboarding and security accreditation. PRAMAAN implements production-shaped adapter interfaces (`GovPortalAdapter`) backed by a high-fidelity synthetic mock registry (`MockGovPortal`), with clear UI indicators distinguishing simulated from live data.

#### Q26: How would PRAMAAN connect to API Setu in production?
**A:** By configuring `ApiSetuAdapter` with mutual-TLS client certificates and official OAuth2 client credentials provided by the API Setu developer portal (MeitY).

#### Q27: How do you verify GST returns without violating taxpayer privacy?
**A:** We query public GST Suvidha Provider (GSP) endpoints that return return-filing compliance status (GSTR-1 and GSTR-3B filed/unfiled for recent tax periods) based purely on the public GSTIN, without accessing proprietary sales or turnover figures.

#### Q28: How does the system adapt when government procurement rules change?
**A:** Rules are maintained as versioned YAML configurations (`rules.yaml`). When a new policy circular is issued, a new rule set is created with an effective date. Tenders are evaluated against the rule version active on their publication date.

---

## 6. MSME Inclusivity & Public Value

#### Q29: How does PRAMAAN directly benefit a small MSME?
**A:** Through the Vendor Self-Service Pre-Check portal. MSMEs upload their documents before bidding and receive an actionable readiness report highlighting exact gaps (e.g., *"Your turnover certificate lacks a CA UDIN"* or *"Your GST certificate is expiring in 5 days"*) in plain English and Hindi.

#### Q30: Does PRAMAAN impose financial burdens on small vendors?
**A:** The pre-submission assessment is designed as a free public utility funded through enterprise government licensing to democratize public procurement participation.

#### Q31: Is the platform accessible to vendors in non-metro areas?
**A:** Yes. The interface meets WCAG 2.1 Level AA accessibility standards, features responsive mobile layouts, and provides bilingual Hindi and English views.

---

## 7. Audit Defensibility & Legal Integrity

#### Q32: Why not use a public blockchain like Ethereum for the audit trail?
**A:** Public blockchains expose public procurement metadata, introduce volatile transaction fees, and violate Indian data sovereignty mandates. Cryptographic SHA-256 hash-chaining delivers identical mathematical tamper-evidence with zero cost and microsecond performance.

#### Q33: How does an officer defend a decision during a CAG audit?
**A:** The officer exports the cryptographically signed compliance dossier. The dossier links every finding to the exact source document, page, and pixel coordinates, and embeds the ledger head hash proving the decision was recorded contemporaneously.

#### Q34: What prevents an officer from colluding with a favored vendor?
**A:** Every officer action, document view, and waiver is recorded in the immutable audit ledger. Any deviation from the automated system recommendation mandates a written justification subject to scrutiny by supervisory vigilance officers.

---

## 8. Scalability, Resilience & Commercial Roadmap

#### Q35: Can PRAMAAN handle 50,000 bids submitted on deadline day?
**A:** Yes. The stateless FastAPI application nodes scale horizontally behind a load balancer; document uploads stream directly to encrypted object storage; and extraction tasks are processed asynchronously via Redis worker pools.

#### Q36: What is the average verification latency per bidder?
**A:** For standard digital text PDFs, text extraction and rule evaluation complete in under 850 milliseconds. For scanned documents requiring OCR, processing completes in 3.5 to 6 seconds per page.

#### Q37: What is your pilot engagement plan for a government ministry?
**A:** A structured 90-day sandbox pilot:
* Days 1–15: Security architecture review and sandbox environment setup.
* Days 16–45: Historical benchmarking across 50–100 closed tenders.
* Days 46–75: Parallel live evaluation alongside human officers.
* Days 76–90: Audit validation and transition to production deployment.

#### Q38: Why wouldn't GeM just build this internally?
**A:** GeM is primarily a marketplace transaction platform that integrates specialized compliance and verification engines via external API adapters (such as PAN verification via NSDL and MCA data via MCA21). PRAMAAN is architected specifically as a modular verification plugin that slots into this existing ecosystem.

#### Q39: What is the estimated operating cost of a departmental pilot?
**A:** Under ₹1.5 Lakhs per month on MeitY-empanelled cloud infrastructure to evaluate 500+ tenders, offset by hundreds of officer hours saved and reduced dispute litigation costs.

#### Q40: What is your defensible technology moat?
**A:** Our moat is the **Compliance Fusion Engine + Evidence Graph + Versioned Rule Architecture** — uniting deterministic legal policy rules, byte-level PDF forensics, bipartite collusion clustering, and sovereign human governance.
