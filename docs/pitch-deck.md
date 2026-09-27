# PRAMAAN — 12-Slide SIH Grand Finale Pitch Deck

---

## Slide 1: The Title & Mission
* **Headline:** PRAMAAN (प्रमाण) — AI-Powered GeM Bid Compliance & Procurement Intelligence Platform
* **Subtitle:** *“Understand the tender. Verify the bid. Prove the decision.”*
* **Visual Direction:** Sleek, institutional navy and slate layout. Mockup showing the split-screen evidence viewer with highlighted bounding boxes alongside the tamper-evident audit ledger.
* **Core Tagline:** Transforming Indian public procurement from an opaque, clerical bottleneck into an evidence-backed, auditable digital infrastructure.
* **Presenter Note:** "Good morning, respected jury members. Today we present PRAMAAN, an evidence-backed compliance verification platform that protects public funds while opening government procurement to genuine Indian MSMEs."

---

## Slide 2: The Real Procurement Crisis
* **Headline:** Billions in Public Procurement. Paralyzed by Paperwork.
* **The Dual Crisis:**
  * **For MSMEs:** Over 18% of technically capable MSMEs face rejection on GeM due to preventable documentary errors — an expired certificate, a minor name formatting discrepancy, or an overlooked clause.
  * **For Evaluating Officers:** Officers must manually cross-verify 40+ multi-page PDFs across 12 statutory registries under strict statutory deadlines.
  * **For Integrity & Vigilance:** Bid-rigging rings and front companies pass individual checks while sharing banking credentials and authorized signatories behind the scenes.
* **Stat Callout:** Over 18% avoidable technical disqualification rate for smaller MSMEs.

---

## Slide 3: The Solution — PRAMAAN
* **Headline:** An Evidence-Backed Decision Engine for Public Procurement
* **The Three Pillars:**
  1. **UNDERSTAND (Tender Intelligence):** Converts unstructured tender notices and Additional Terms & Conditions (ATC) into machine-verifiable requirements.
  2. **VERIFY (Compliance Fusion):** Merges deterministic legal rules, layout-aware OCR, PKI digital signature checks, and byte-level tamper detection.
  3. **PROVE (Audit Ledger):** Preserves an immutable, SHA-256 hash-chained audit trail where human officers retain final sovereign adjudication authority.

---

## Slide 4: The Six-Layer Architecture
* **Headline:** Beyond "AI Reading PDFs" — A Multi-Layer Intelligence Infrastructure
* **Architecture Diagram:**
  * Layer 1: Tender Intelligence (Clause segmentation & threshold parsing)
  * Layer 2: Vendor Digital Compliance Twin (Persistent statutory identity profile)
  * Layer 3: Compliance Fusion Engine (Declarative YAML rules + bounded AI explanations)
  * Layer 4: Integrity Intelligence (pyHanko PKI verification + pikepdf tamper detection)
  * Layer 5: Sovereign Human Decision (Officer review, split-screen evidence, mandatory justification)
  * Layer 6: Tamper-Evident Audit Fabric (Append-only SHA-256 cryptographic chain)

---

## Slide 5: What Makes PRAMAAN Defensibly Unique
* **Headline:** Architectural Innovation Where Trust is Non-Negotiable
* **Comparison Matrix:**
  * **Deterministic Rules vs. AI Black Box:** AI extracts and assists; policy rules and authorized humans decide.
  * **Byte-Level PDF Forensics:** Detects post-signing incremental modifications and modified xref tables that evade visual inspection.
  * **Cross-Bidder Collusion Intelligence:** Builds a bipartite graph connecting competing bidders to common bank accounts, IFSCs, and signatories.
  * **Sovereign-First Air-Gapped Mode:** Operates 100% offline without external commercial LLMs (`LLM_PROVIDER=offline`).

---

## Slide 6: The Hero Demo — "Supply of Industrial Pumps"
* **Headline:** 7 Bidders. Real Scenarios. Flawless Discrimination.
* **Demonstration Profiles:**
  * **CleanCorp (Score: 95.0 · Qualify):** Baseline clean vendor; valid digital signature; matched PAN/Udyam.
  * **Borderline Traders (Score: 87.5 · Needs Review):** Missing Q3 GST return; 82% fuzzy name match flagged for human waiver.
  * **FraudFillers (Score: 25.0 · Disqualify):** Forged GST cert; invalid PKI signature; post-signing tamper detected.
  * **FrontRunner & QuickSpares:** Individually compliant (>90), but caught by Collusion Engine sharing Bank Account #HDFC5020...

---

## Slide 7: Explainable AI & Evidence Linking
* **Headline:** Every Finding Links to the Exact Document, Page, and Pixel
* **Visual:** Split-screen screenshot showing yellow highlighted bounding box on the GST registration certificate.
* **Key Capabilities:**
  * Deep-linked provenance: clicking any statutory check opens the source PDF with exact bounding box coordinates.
  * Decomposed scoring: each score is a transparent weighted sum of statutory, technical, and financial criteria.
  * Reversible human overrides: officers can grant waivers, but must provide written justifications committed to the ledger.

---

## Slide 8: Government Integration Reality
* **Headline:** Production-Shaped Architecture Built for India's Digital Stack
* **Transparency Commitment:** Clearly distinguishes LIVE vs. MOCK vs. AUTHORIZATION REQUIRED.
* **Adapter Seam (`GovPortalAdapter`):**
  * Seamlessly swaps from `MockGovPortal` (offline demo) to `ApiSetuAdapter` (live production gateway).
  * Direct schema compatibility with API Setu (ITD PAN, GSTN, Udyam) and DigiLocker root CAs.
  * Field-level Fernet encryption and PII log redaction to protect sensitive vendor data.

---

## 9. Slide 9: Quantifiable Impact & MSME Enablement
* **Headline:** Driving Speed, Fairness, and Treasury Savings
* **Measurable Targets:**
  * **90% Reduction** in technical evaluation turnaround time (from 5–7 days down to under 30 minutes).
  * **40% Reduction** in avoidable MSME clerical rejections via the Pre-Check Self-Assessment portal.
  * **100% Audit Readiness:** Instantaneous generation of cryptographically signed compliance dossiers for CAG/CVC review.
  * **Bilingual Empowerment:** Native English and Hindi interfaces to ensure regional inclusivity.

---

## Slide 10: Enterprise Security & Scalability
* **Headline:** Hardened for 50,000+ Daily Procurement Verifications
* **Security & Reliability Highlights:**
  * Stateless FastAPI microservices with Redis asynchronous worker queues.
  * STRIDE threat-modeled with defenses against PDF zip bombs and prompt-injection payloads.
  * Cryptographic SHA-256 hash-chained ledger with automated break detection (`/api/v1/audit/verify`).
  * 82 backend pytest cases + frontend vitest suites running in automated GitHub Actions CI/CD.

---

## Slide 11: Feasibility, Business Model & Roadmap
* **Headline:** A Pragmatic Path to National Deployment
* **Implementation Phasing:**
  * **Months 1–3 (Pilot):** Single-department PSU pilot (e.g., Oil & Gas / Power PSU) on 100 historical tenders.
  * **Months 4–6 (Integration):** API Setu mutual-TLS onboarding & Vendor Pre-Submission portal launch.
  * **Months 7–12 (National Scale):** Federated multi-department deployment across GeM core infrastructure.
* **Business Model:** Public enterprise licensing per procurement directorate, supplemented by free MSME pre-check tooling.

---

## Slide 12: The Vision & Closing Call to Action
* **Headline:** From Bid Uncertainty to Evidence-Backed Procurement
* **Closing Statement:**
  > *“PRAMAAN eliminates the heartbreak of capable MSMEs losing tenders to paperwork errors, while giving government officers an unassailable shield of evidence.”*
* **Summary Tagline:** **Understand the tender. Verify the bid. Prove the decision.**
* **Repository:** `https://github.com/sakshamp413-hash/gem-bid-compliance-platform`
